package ch.unibas.dmi.dbis.fds._2pc;

import java.sql.Connection;
import javax.sql.XAConnection;
import javax.transaction.xa.XAException;
import javax.transaction.xa.XAResource;
import javax.transaction.xa.Xid;
import java.sql.SQLException;
import java.sql.PreparedStatement;
import java.sql.ResultSet;
import java.sql.SQLException;


/**
 * Check the XA stuff here --> https://docs.oracle.com/cd/B14117_01/java.101/b10979/xadistra.htm
 *
 * @author Alexander Stiemer (alexander.stiemer at unibas.ch)
 */
public class OracleXaBank extends AbstractOracleXaBank {


    public OracleXaBank(final String BIC, final String jdbcConnectionString, final String dbmsUsername, final String dbmsPassword) throws SQLException {
        super(BIC, jdbcConnectionString, dbmsUsername, dbmsPassword);
    }


    @Override
    public float getBalance(final String iban) throws SQLException {
        XAConnection openxa = this.getXaConnection();
        String query = "SELECT balance\n" +
                "FROM account\n" +
                "WHERE iban = ?\n";

        try {
            Connection connection = this.getXaConnection().getConnection();
            PreparedStatement statement = connection.prepareStatement(query);
            statement.setString(1, iban);
            statement.executeQuery();
            try (ResultSet result = statement.executeQuery()) {

                if (result.next()) {
                    return result.getFloat("Balance");
                }
            }

        } catch (SQLException e) {
            throw new RuntimeException(e);
        }
        throw new SQLException("IBAN not found: " + iban);
    }


    @Override
    public void transfer(
            final AbstractOracleXaBank TO_BANK,
            final String ibanFrom,
            final String ibanTo,
            final float value
    ) {
        if (!Float.isFinite(value) || value <= 0) {
            throw new IllegalArgumentException("Transfer amount must be positive and finite");
        }

        Xid xidX = null;
        Xid xidY = null;

        boolean activeX = false;
        boolean activeY = false;

        boolean commitDecided = false;

        int voteX = -1;
        int voteY = -1;

        try {
            // ==========================================
            // 1. START TRANSACTIONS
            // ==========================================

            xidX = this.startTransaction();
            activeX = true;

            xidY = TO_BANK.startTransaction(xidX);
            activeY = true;

            // ==========================================
            // 2. EXECUTE SQL OPERATIONS
            // ==========================================

            // Debit money from Bank X
            try (Connection connectionX = this.getXaConnection().getConnection();
                 PreparedStatement debit = connectionX.prepareStatement(
                         "UPDATE account SET Balance = Balance - ? WHERE IBAN = ?"
                 )) {

                debit.setFloat(1, value);
                debit.setString(2, ibanFrom);

                int updatedRows = debit.executeUpdate();

                if (updatedRows != 1) {
                    throw new SQLException("Source account not found: " + ibanFrom);
                }
            }

            // Credit money to Bank Y
            try (Connection connectionY = TO_BANK.getXaConnection().getConnection();
                 PreparedStatement credit = connectionY.prepareStatement(
                         "UPDATE account SET Balance = Balance + ? WHERE IBAN = ?"
                 )) {

                credit.setFloat(1, value);
                credit.setString(2, ibanTo);

                int updatedRows = credit.executeUpdate();

                if (updatedRows != 1) {
                    throw new SQLException("Destination account not found: " + ibanTo);
                }
            }

            // ==========================================
            // 3. END TRANSACTION BRANCHES
            // ==========================================

            this.endTransaction(xidX, false);
            activeX = false;

            TO_BANK.endTransaction(xidY, false);
            activeY = false;

            // ==========================================
            // 4. PHASE 1: PREPARE
            // ==========================================

            XAResource resourceX = this.getXaResource();
            XAResource resourceY = TO_BANK.getXaResource();

            voteX = resourceX.prepare(xidX);
            voteY = resourceY.prepare(xidY);

            boolean preparedX =
                    voteX == XAResource.XA_OK ||
                            voteX == XAResource.XA_RDONLY;

            boolean preparedY =
                    voteY == XAResource.XA_OK ||
                            voteY == XAResource.XA_RDONLY;

            if (!preparedX || !preparedY) {
                throw new XAException("One or more banks did not prepare successfully");
            }

            // ==========================================
            // 5. PHASE 2: COMMIT
            // ==========================================

            // Both banks have voted successfully.
            // From this point onward, rollback is no
            // longer an appropriate recovery strategy.
            commitDecided = true;

            if (voteX == XAResource.XA_OK) {
                resourceX.commit(xidX, false);
            }

            if (voteY == XAResource.XA_OK) {
                resourceY.commit(xidY, false);
            }

            System.out.println(
                    "Successfully transferred " + value +
                            " from " + ibanFrom +
                            " to " + ibanTo
            );

        } catch (Exception e) {

            // ==========================================
            // 6. ROLLBACK ON FAILURE
            // ==========================================

            if (!commitDecided) {

                // End still-active transaction branches
                if (activeX && xidX != null) {
                    try {
                        this.endTransaction(xidX, true);
                    } catch (XAException ex) {
                        e.addSuppressed(ex);
                    }
                }

                if (activeY && xidY != null) {
                    try {
                        TO_BANK.endTransaction(xidY, true);
                    } catch (XAException ex) {
                        e.addSuppressed(ex);
                    }
                }

                // Roll back Bank X
                if (xidX != null && voteX != XAResource.XA_RDONLY) {
                    try {
                        this.getXaResource().rollback(xidX);
                    } catch (XAException ex) {
                        e.addSuppressed(ex);
                    }
                }

                // Roll back Bank Y
                if (xidY != null && voteY != XAResource.XA_RDONLY) {
                    try {
                        TO_BANK.getXaResource().rollback(xidY);
                    } catch (XAException ex) {
                        e.addSuppressed(ex);
                    }
                }
            }

            throw new RuntimeException(
                    commitDecided
                            ? "Transfer commit failed; transaction outcome requires recovery"
                            : "Transfer failed and rollback was attempted",
                    e
            );
        }

    }
}
