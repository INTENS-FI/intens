package fi.vtt.intens.o4j_client.eval;

import static org.junit.Assert.*;

import org.junit.After;
import org.junit.Before;
import org.junit.Test;

import eu.cityopt.sim.eval.Evaluator;
import eu.cityopt.sim.eval.Namespace;

/**
 * For these to work the simsvc server must be running at the url
 * given in test_model.yaml. 
 * @author ttekth
 *
 */
public class IntensRunnerTest extends TestBase {
    private IntensFactory fac;
    private IntensModel model;
    private Namespace ns;
    private IntensRunner runner;
    
    @Before
    public void setup() throws Exception {
        fac = inj.getInstance(IntensFactory.class);
        try (var in = getModelStream()) {
            model = fac.loadModel(in);
        }
        ns = new Namespace(new Evaluator(),
                model.getDefaults().timeOrigin);
        runner = fac.mgr.makeRunner(model, ns);
    }
    
    @After
    public void teardown() throws Exception {
        closeAll(runner, model, fac);
    }

    @Test
    public void test() {
        fail("Not yet implemented");
    }
}
