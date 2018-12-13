package fi.vtt.intens.o4j_client.eval;

import java.io.IOException;

import okhttp3.Response;

/**
 * An exception class for HTTP errors.
 */
public class HttpException extends IOException {
    private static final long serialVersionUID = 1L;
    
    public Integer httpStatus;

    public HttpException() {}
    
    public HttpException(int status, String message) {
        super(message);
        httpStatus = status;
    }

    public HttpException(Throwable cause) {
        super(cause);
    }

    public HttpException(int status, String message, Throwable cause) {
        super(message, cause);
        httpStatus = status;
    }

    /**
     * Create a new exception with the status code and message from
     * an {@link okhttp3.Response}.  The message is the response body.
     * Does not close the response; best used inside a try-with-resources
     * that manages resp.
     */
    public HttpException(Response resp) throws IOException {
        this(resp.code(), resp.body().string());
    }

    @Override
    public String getMessage() {
        var msg = super.getMessage();
        if (httpStatus != null)
            msg += "\nHTTP status code: " + httpStatus + "\n";
        return msg;
    }
}
