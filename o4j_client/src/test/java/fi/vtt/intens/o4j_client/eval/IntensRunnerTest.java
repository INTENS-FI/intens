package fi.vtt.intens.o4j_client.eval;

import static org.junit.Assert.*;

import org.junit.After;
import org.junit.Before;
import org.junit.Ignore;
import org.junit.Test;
import org.slf4j.Logger;
import org.slf4j.LoggerFactory;

import eu.cityopt.sim.eval.Evaluator;
import eu.cityopt.sim.eval.ExternalParameters;
import eu.cityopt.sim.eval.Namespace;
import eu.cityopt.sim.eval.SimulationFailure;
import eu.cityopt.sim.eval.SimulationInput;
import eu.cityopt.sim.eval.SimulationOutput;
import eu.cityopt.sim.eval.SimulationResults;
import eu.cityopt.sim.eval.Type;

/**
 * For these to work the simsvc server must be running at the url
 * given in test_model.yaml. 
 * @author ttekth
 *
 */
//@Ignore("Simsvc server required")
public class IntensRunnerTest extends TestBase {
    private static Logger
        logger = LoggerFactory.getLogger(IntensRunnerTest.class);
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
    public void test() throws Exception {
        var comp = new Namespace.Component();
        comp.inputs.put("x", Type.INTEGER);
        comp.inputs.put("y", Type.INTEGER);
        comp.outputs.put("sum", Type.INTEGER);
        ns.components.put("c", comp);
        var xp = new ExternalParameters(ns);
        var in = new SimulationInput(xp);
        in.put("c", "x", 1);
        in.put("c", "y", 2);
        logger.info("Launching job");
        IntensJob job = runner.start(in);
        logger.info("Launched, id = " + job.jobid);
        SimulationOutput out = job.get();
        logger.info("Log:\n" + out.getMessages() + "(EOF)\n");
        if (out instanceof SimulationResults) {
            var res = (SimulationResults)out;
            logger.info("Success, sum = " + res.getString("c", "sum"));
        } else {
            var f = (SimulationFailure)out;
            fail((f.permanent ? "Permanent" :  "Temporary")
                 + " failure: " + f.reason); 
        }
    }
}
