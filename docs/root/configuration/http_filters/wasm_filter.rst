.. _config_http_filters_wasm:

WebAssembly
===========

Overview
--------

TODO: add text about high level design principal and feature set.

This `video talk <https://youtu.be/XdWmm_mtVXI>`_ has great introduction about archtecture of WebAssembly runtime integration.

Configuration
-------------

* :ref:`v2 API reference <envoy_api_msg_config.filter.http.wasm.v2.Wasm>`
* This filter should be configured with name *envoy.wasm*.

Example
-------

An example C++ WASM filter could be found `here <https://github.com/envoyproxy/envoy-wasm/tree/19b9fd9a22e27fcadf61a06bf6aac03b735418e6/examples/wasm>`_.

To implement a WASM filter:

* Create a `filter context class <https://github.com/envoyproxy/envoy-wasm/blob/19b9fd9a22e27fcadf61a06bf6aac03b735418e6/examples/wasm/envoy_filter_http_wasm_example.cc#L7>`_ which inherits the `base context class <https://github.com/envoyproxy/envoy-wasm/blob/19b9fd9a22e27fcadf61a06bf6aac03b735418e6/api/wasm/cpp/proxy_wasm_impl.h#L225>`_.
* Override :ref:`context API <config_http_filters_wasm_context_api>` methods to handle corresponding initialization and stream events from host.
* Implement a `NewContext method <https://github.com/envoyproxy/envoy-wasm/blob/19b9fd9a22e27fcadf61a06bf6aac03b735418e6/examples/wasm/envoy_filter_http_wasm_example.cc#L22>`_ for the construction of filter :ref:`context object <config_http_filters_wasm_context_object>`.

.. _config_http_filters_wasm_context_object:

Context object
--------------

WASM module is running in a stack-based virtual machine and its memory is isolated from the host environment. 
All interactions between host and WASM module are through functions and callbacks wrapped by context object. 

Context object acts as the target for calls at both sides. At bootstrap time, a root context with id 0 is created. 
The root context has the same lifetime as the VM/runtime instance and acts as target for any interactions which happen at initial setup or outlive a request. 
At request time, a context with incremental id from 1 is created for each stream. Stream context has the same lifetime as the stream and acts as target for interactions that are local to that stream.

.. image:: /_static/wasm_context.svg
  :width: 100%

.. _config_http_filters_wasm_context_api:

Context API
-----------

Root Context API
~~~~~~~~~~~~~~~~

onConfigure
^^^^^^^^^^^

.. code-block:: cpp

    void onConfigure(std::unique_ptr<WasmData> configuration)

Called when host loads the WASM module. If the VM that the module running in has not been configured, `onConfigure` is called first with :ref:`VM config <envoy_api_field_config.wasm.v2.VmConfig.initial_configuration>`,
then a second call will be invoked to pass in :ref:`module config <envoy_api_field_config.wasm.v2.WasmConfig.configuration>`. 

If :ref:`VM is shared <config_http_filters_wasm_vm_sharing>` by multiple modules and has already been configured via other WASM filter in the chain, `onConfigure` will only be called once with module config. 

onStart
^^^^^^^

.. code-block:: cpp

    void onStart()

Called after finishing loading WASM module and before serving any stream events.

Stream Context API
~~~~~~~~~~~~~~~~~~

The following functions are called in order during a stream lifetime.

onCreate
^^^^^^^^

.. code-block:: cpp

    void onCreate()

Called at the beginning of filter chain iteration. Indicates creation of the new stream context.

.. _config_http_filters_wasm_context_api_onrequestheaders:

onRequestHeaders
^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void onRequestHeaders()

Called when headers are decoded. Returns `FilterHeadersStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L27>`_ 
to determine how filter chain iteration proceeds. Request Headers could be fetched from host via :ref:`request header API <config_http_filters_wasm_request_header_api>`.

.. _config_http_filters_wasm_context_api_onrequestbody:

onRequestBody
^^^^^^^^^^^^^

.. code-block:: cpp
   
    FilterDataStatus onRequestBody(size_t body_buffer_length, bool end_of_stream) 

Called when request body is decoded. *body_buffer_length* is used to indicate size of decoded request body. 
*end_of_stream* indicates if this is the last data frame. Returns `FilterDataStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L66>`_
to determine how filter chain iteration proceeds. Request body could be fetched from host via :ref:`body API <config_http_filters_wasm_body_api>`.

.. _config_http_filters_wasm_context_api_onrequesttrailers:

onRequestTrailers
^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    FilterTrailersStatus onRequestTrailers()

Called when request trailers are decoded. Returns FilterTrailerStatus `FilterTrailerStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L104>`_
to determine how filter chain iteration proceeds. Request trailers could be fetched via :ref:`request trailer API <config_http_filters_wasm_response_trailer_api>`.

.. _config_http_filters_wasm_context_api_onresponseheaders:

onResponseHeaders
^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void onResponseHeaders()

Called when headers are decoded. Returns `FilterHeadersStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L27>`_ 
to determine how filter chain iteration proceeds. Response headers could be fetched from host via :ref:`response header API <config_http_filters_wasm_response_header_api>`.

.. _config_http_filters_wasm_context_api_onresponsebody:

onResponseBody
^^^^^^^^^^^^^^

.. code-block:: cpp
   
    FilterDataStatus onResponseBody(size_t body_buffer_length, bool end_of_stream) 

Called when response body is decoded. *body_buffer_length* is used to indicate size of decoded response body. 
*end_of_stream* indicates if this is the last data frame. Returns `FilterDataStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L66>`_
to determine how filter chain iteration proceeds. Response body could be fetched from host via :ref:`body API <config_http_filters_wasm_body_api>`.

.. _config_http_filters_wasm_context_api_onresponsetrailers:

onResponseTrailers
^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    FilterTrailersStatus onResponseTrailers()

Called when response trailers are decoded. Returns FilterTrailerStatus `FilterTrailerStatus <https://github.com/envoyproxy/envoy/blob/5d3214d4d8e1d77937f0f1278d3ac816d9a3d888/include/envoy/http/filter.h#L104>`_
to determine how filter chain iteration proceeds. Response trailers could be fetched via :ref:`response trailer API <config_http_filters_wasm_response_trailer_api>`.

onDone
^^^^^^

.. code-block:: cpp

    void onDone()

Called after stream is ended or reset. All stream info will not be changed any more and is safe for access logging.

.. _config_http_filters_wasm_context_api_onlog:

onLog
^^^^^

.. code-block:: cpp

    void onLog()

Called to log any stream info. Several types of stream info are available from API: 
Request headers could be fetched from host via :ref:`request header API <config_http_filters_wasm_request_header_api>`.
Response headers could be fetched from host via :ref:`response header API <config_http_filters_wasm_response_header_api>`.
Response trailers could be fetched via :ref:`response trailer API <config_http_filters_wasm_response_trailer_api>`.
Streaminfo could be fetched via :ref:`streaminfo API <config_http_filters_wasm_streaminfo_api>`.

onDelete
^^^^^^^^

.. code-block:: cpp

    void onDelete()

Called after logging is done. This call indicates no more handler will be called on the stream context and it is up for deconstruction, 
The stream context needs to make sure all async events are cleaned up, such as network calls, timers.

Application log API
-------------------

log*
~~~~
.. code-block:: cpp

    void LogTrace(const std::string& logMessage)
    void LogDebug(const std::string& logMessage)
    void LogInfo(const std::string& logMessage)
    void LogWarn(const std::string& logMessage)
    void LogError(const std::string& logMessage)
    void LogCritical(const std::string& logMessage)

Logs a message using Envoy's application logging. *logMessage* is a string to log.

.. _config_http_filters_wasm_header_api:

Header API
----------

.. _config_http_filters_wasm_request_header_api:

Request header API
~~~~~~~~~~~~~~~~~~

addRequestHeader
^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void addRequestHeader(StringView key, StringView value)

Adds a new request header with the key and value if header does not exist, or append the value if header exists.
Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>`.

replaceRequestHeader
^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void replaceRequestHeader(StringView key, StringView value)

Replaces the value of an existing request header with the given key, or create a new request header with the key and value if not existing.
Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>`.

removeRequestHeader
^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void removeRequestHeader(StringView key)

Removes request header with the given key. No-op if the request header does not exist.
Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>`.

setRequestHeaderPairs
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void setRequestHeaderPairs(const HeaderStringPairs &pairs)

Sets request headers with the given header pairs. For each header key value pair, it acts the same way as replaceRequestHeader.
Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>`.

getRequestHeader
^^^^^^^^^^^^^^^^

.. code-block:: cpp

    WasmDataPtr getRequestHeader(StringView key)

Gets value of header with the given key. Returns empty string if header does not exist. 
Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.

getRequestHeaderPairs
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    WasmDataPtr getRequestHeaderPairs()

Gets all header pairs. Note this method would only be effective when called in :ref:`onRequestHeader <config_http_filters_wasm_context_api_onrequestheaders>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.

.. _config_http_filters_wasm_response_header_api:

Response header API
~~~~~~~~~~~~~~~~~~~

addResponseHeader
^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void addResponseHeader(StringView key, StringView value)
 
Adds a new response header with the key and value if header does not exist, or append the value if header exists.
Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>`.
 
replaceResponseHeader
^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void replaceResponseHeader(StringView key, StringView value)
 
Replaces the value of an existing response header with the given key, or create a new response header with the key and value if not existing.
Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>`.
 
removeResponseHeader
^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void removeResponseHeader(StringView key)
 
Removes response header with the given key. No-op if the response header does not exist.
Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>`.
 
setResponseHeaderPairs
^^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void setResponseHeaderPairs(const HeaderStringPairs &pairs)
 
Sets response headers with the given header pairs. For each header key value pair, it acts the same way as replaceResponseHeader.
Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>`.
 
getResponseHeader
^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   WasmDataPtr getResponseHeader(StringView key)
 
Gets value of header with the given key. Returns empty string if header does not exist.
Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.
 
getResponseHeaderPairs
^^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   WasmDataPtr getResponseHeaderPairs()
 
Gets all header pairs. Note this method would only be effective when called in :ref:`onResponseHeader <config_http_filters_wasm_context_api_onresponseheaders>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.

.. _config_http_filters_wasm_response_trailer_api:

Request trailer API
~~~~~~~~~~~~~~~~~~~

addRequestTrailer
^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void addRequestTrailer(StringView key, StringView value)

Adds a new request trailer with the key and value if trailer does not exist, or append the value if trailer exists.
Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

replaceRequestTrailer
^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void replaceRequestTrailer(StringView key, StringView value)

Replaces the value of an existing request trailer with the given key, or create a new request trailer with the key and value if not existing.
Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

removeRequestTrailer
^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void removeRequestTrailer(StringView key)

Removes request trailer with the given key. No-op if the request trailer does not exist.
Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

setRequestTrailerPairs
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    void setRequestTrailerPairs(const HeaderStringPairs &pairs)

Sets request trailers with the given trailer pairs. For each trailer key value pair,it acts the same way as replaceRequestHeader.
Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

getRequestTrailer
^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    WasmDataPtr getRequestTrailer(StringView key)

Gets value of trailer with the given key. Returns empty string if trailer does not exist.
Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

getRequestTrailerPairs
^^^^^^^^^^^^^^^^^^^^^^

.. code-block:: cpp

    WasmDataPtr getRequestTrailerPairs()

Gets all trailer pairs. Note this method would only be effective when called in :ref:`onRequestTrailers <config_http_filters_wasm_context_api_onrequesttrailers>`.

Response trailer API
~~~~~~~~~~~~~~~~~~~~

addResponseTrailer
^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void addResponseTrailer(StringView key, StringView value)
 
Adds a new response trailer with the key and value if trailer does not exist, or append the value if trailer exists.
Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>`.
 
replaceResponseTrailer
^^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void replaceResponseTrailer(StringView key, StringView value)
 
Replaces the value of an existing response trailer with the given key, or create a new response trailer with the key and value if not existing.
Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>`.
 
removeResponseTrailer
^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void removeResponseTrailer(StringView key)
 
Removes response trailer with the given key. No-op if the response trailer does not exist.
Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>`.
 
setResponseTrailerPairs
^^^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   void setResponseTrailerPairs(const TrailerStringPairs &pairs)
 
Sets response trailers with the given trailer pairs. For each trailer key value pair, it acts the same way as replaceResponseTrailer.
Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>`.
 
getResponseTrailer
^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp
 
   WasmDataPtr getResponseTrailer(StringView key)
 
Gets value of trailer with the given key. Returns empty string if trailer does not exist.
Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.
 
getResponseTrailerPairs
^^^^^^^^^^^^^^^^^^^^^^^
 
.. code-block:: cpp

   WasmDataPtr getResponseTrailerPairs()
 
Gets all trailer pairs. Note this method would only be effective when called in :ref:`onResponseTrailer <config_http_filters_wasm_context_api_onresponsetrailers>` and
:ref:`onLog <config_http_filters_wasm_context_api_onlog>`.

.. _config_http_filters_wasm_body_api:

Body API
--------

getRequestBodyBufferBytes
~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: cpp

   WasmDataPtr getRequestBodyBufferBytes(size_t start, size_t length)

Returns buffered request body. This copies segment of request body. *start* is an integer and supplies the body buffer start index to copy. 
*length* is an integer and supplies the buffer length to copy. This method is effective when calling from :ref:`onRequestBody <config_http_filters_wasm_context_api_onrequestbody>`.

getResponseBodyBufferBytes
~~~~~~~~~~~~~~~~~~~~~~~~~~

.. code-block:: cpp

   WasmDataPtr getResponseBodyBufferBytes(size_t start, size_t length)

Returns buffered response body. This copies segment of response body. *start* is an integer and supplies the body buffer start index to copy.
*length* is an integer and supplies the buffer length to copy. This method is effective when calling from :ref:`onResponseBody <config_http_filters_wasm_context_api_onresponsebody>`.

Metadata API
------------

Route metadata API
~~~~~~~~~~~~~~~~~~

requestRouteMetadataValue
^^^^^^^^^^^^^^^^^^^^^^^^^

google::protobuf::Value requestRouteMetadataValue(StringView key);
Get the value from metadata from upstream route metadata with the given key. Note every call to this function costs copy of value into vm memory.

google::protobuf::Value responseRouteMetadataValue(StringView key);
Same


Node metadata API
~~~~~~~~~~~~~~~~~

Request metadata API
~~~~~~~~~~~~~~~~~~~~

Response metadata API
~~~~~~~~~~~~~~~~~~~~~

Log metadata API
~~~~~~~~~~~~~~~~

.. _config_http_filters_wasm_streaminfo_api:

StreamInfo API
--------------

.. inline WasmDataPtr getProtocol(StreamType type)

HTTP API
--------

gRPC API
--------

Timer API
---------

Metric API
----------

Counter
~~~~~~~

Gauge
~~~~~

Histogram
~~~~~~~~~

Data Structure
--------------

WASM module out of tree
-----------------------

TODO: add a example about out of tree WASM module example

.. _config_http_filters_wasm_vm_sharing:

VM Sharing
----------

TODO: add instruction about vm sharing