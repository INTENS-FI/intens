package fi.vtt.intens.o4j_client.eval;

import static org.junit.Assert.*;

import java.io.InputStream;

import org.junit.Test;

import com.google.inject.Guice;
import com.google.inject.Injector;

public class IntensManagerTest {
    private Injector inj = Guice.createInjector(new JacksonYamlModule());

    @Test
    public void testParseModel() throws Exception {
        IntensManager mgr = inj.getInstance(IntensManager.class);
        IntensModel mdl;
        try (InputStream str = this.getClass().getResourceAsStream(
                "/test_model.yaml")) {
            mdl = mgr.parseModel(null, str);
        }
        mgr.om.writeValue(System.out, mdl);
        assertSame("Model simulator manager not set correctly",
                   mgr, mdl.getSimulatorManager());
    }
}
