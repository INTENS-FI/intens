package fi.vtt.intens.o4j_client.eval;

import static org.junit.Assert.*;

import org.junit.Test;

public class IntensManagerTest extends TestBase {
    @Test
    public void testParseModel() throws Exception {
        try (var fac = inj.getInstance(IntensFactory.class);
             var in = getModelStream();
             var mdl = fac.loadModel(in)) {
            fac.mgr.modelOM.writeValue(System.out, mdl);
            assertSame("Model simulator manager not set correctly",
                    fac.mgr, mdl.getSimulatorManager());
            assertNotNull("Null defaults", mdl.getDefaults());
            assertNotNull("Null descriptions", mdl.descriptions);
        }
    }
}
