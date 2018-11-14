package fi.vtt.intens.o4j_client.eval;

import java.io.Closeable;
import java.io.IOException;
import java.io.InputStream;

import com.google.inject.Guice;
import com.google.inject.Injector;

public class TestBase {
    protected Injector inj = Guice.createInjector(
                new IntensJacksonModule());

    public InputStream getModelStream() {
        return getClass().getResourceAsStream("/test_model.yaml");
    }

    /**
     * Close all the Closeables.
     * Nulls are ignored.  All non-null cs are closed in the order given,
     * even if some throw.  The last exception is then rethrown.  If multiple
     * closings throw, each exception but the last is suppressed by the next.
     * 
     * @throws IOException from the last close that threw
     */
    public static void closeAll(Closeable... cs) throws IOException {
        Exception ex = null;
        for (var c : cs)
            if (c != null)
                try {
                    c.close();
                } catch (RuntimeException | IOException e) {
                    if (ex != null)
                        e.addSuppressed(ex);
                    ex = e;
                }
        if (ex != null) {
            if (ex instanceof IOException)
                throw (IOException)ex;
            else
                throw (RuntimeException)ex;
        }
    }
}
