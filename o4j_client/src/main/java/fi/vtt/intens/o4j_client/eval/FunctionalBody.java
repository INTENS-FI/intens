package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;
import java.io.OutputStream;

import okhttp3.MediaType;
import okhttp3.RequestBody;
import okio.BufferedSink;

/**
 * A functional wrapper around {@link RequestBody}.
 * 
 * @deprecated Currently broken.
 * XXX This is a documented way for doing async posts with OkHttpClient.
 *   And it does not work.
 */
@Deprecated
public class FunctionalBody extends RequestBody {
    public final MediaType mt;
    
    @FunctionalInterface
    interface Writer {
        public void write(OutputStream str) throws IOException;
    }
    public final Writer writer;

    /**
     * @param mt Media type of the body
     * @param writer Produces the body (by writing into an OutputStream).
     */
    public FunctionalBody(MediaType mt, Writer writer) {
        this.mt = mt;
        this.writer = writer;
    }

    @Override
    public MediaType contentType() {return mt;}
    
    @Override
    public void writeTo(BufferedSink sink) throws IOException {
        writer.write(sink.outputStream());
    }
}
