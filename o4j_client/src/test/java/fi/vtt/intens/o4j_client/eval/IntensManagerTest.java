package fi.vtt.intens.o4j_client.eval;

import static org.junit.Assert.*;

import java.io.InputStream;

import org.junit.Test;

import com.google.inject.Guice;
import com.google.inject.Injector;

public class IntensManagerTest {
    private Injector inj = Guice.createInjector(
            new IntensJacksonModule());
    
    public InputStream getModelStream() {
        return getClass().getResourceAsStream("/test_model.yaml");
    }
    
    @Test
    public void testParseModel() throws Exception {
        var fac = inj.getInstance(IntensFactory.class);
        IntensModel mdl;
        try (var in = getModelStream()) {
            mdl = fac.loadModel(in);
        }
        fac.mgr.modelOM.writeValue(System.out, mdl);
        assertSame("Model simulator manager not set correctly",
                   fac.mgr, mdl.getSimulatorManager());
        assertNotNull("Null defaults", mdl.getDefaults());
        assertNotNull("Null descriptions", mdl.descriptions);
    }
}
