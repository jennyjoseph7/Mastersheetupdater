### `executeTaskWithPolling`

A utility function designed to handle asynchronous, long-running backend tasks using a Queue -> Poll -> Result architecture. It automatically submits a task to the service queue, polls the status API until completion, and retrieves the final result.

#### **Function Signature**

**JavaScript**

```
export const executeTaskWithPolling = async (
  service, 
  taskName, 
  payload, 
  onProgress = null,
  options = {}
) => { ... }
```

#### **Parameters**

* **`service`**  *(String)* :  **Required** . The name of the backend service handling the task.
  * *Example:* `"autocrm-short-run-agent"`
* **`taskName`**  *(String)* :  **Required** . The specific task or method to execute within the service.
  * *Example:* `"generate_campaign_idea"`
* **`payload`**  *(Object)* :  **Required** . The request body containing the data for the task. Typically formatted with `args` (Array) and `kwargs` (Object).
  * *Example:* `{ args: ["pre-sales"], kwargs: { text: "Hello" } }`
* **`onProgress`**  *(Function)* :  *Optional* . A callback function that receives real-time status updates from the server. Perfect for updating UI loading states.
  * *Example:* `(msg) => setStatus(msg)`
* **`options`**  *(Object)* :  *Optional* . Configuration settings to control the polling behavior.
  * `intervalMs`  *(Number)* : Time to wait between status checks in milliseconds. Default: `2000` (2 seconds).
  * `maxRetries`  *(Number)* : Maximum number of polling attempts before throwing a timeout error. Default: `60` (approx 2 minutes total wait time).

#### **Returns**

* **`Promise<any>`** : Resolves to the `result` object returned by the `/gryd/result/{task_id}` API once the task successfully completes.

#### **Throws**

* Throws an `Error` if the initial task submission fails or returns no task ID.
* Throws an `Error` if the polling status returns `"failed"` or `"error"`.
* Throws an `Error` if the maximum number of retries (`maxRetries`) is reached without completion (Timeout).

---

### **Usage Example (React Component)**

Here is a standard example of how to use this function inside a component, complete with loading states and error handling:

**JavaScript**

```
import { useState } from "react";
import { executeTaskWithPolling } from "@/utils/api";

export function CampaignGenerator() {
  const [isLoading, setIsLoading] = useState(false);
  const [statusText, setStatusText] = useState("");
  const [result, setResult] = useState(null);

  const handleRunTask = async () => {
    setIsLoading(true);
    setStatusText("Preparing task...");
  
    try {
      const payload = {
        args: ["pre-sales", "Confirm Test Drives"],
        kwargs: { language: "English" },
	runtime_limit: 3600, // Backend timeout setting
        cancellable: true    // Allows the job to be cancelled in the queue
      };

      // Call the utility function
      const finalData = await executeTaskWithPolling(
        "autocrm-short-run-agent",    // 1. Service
        "generate_campaign_idea",     // 2. Task Name
        payload,                      // 3. Payload
        (msg) => setStatusText(msg),  // 4. Progress Callback
        { maxRetries: 90 }            // 5. Options (3 minutes max wait)
      );

      // Task complete! Handle the result
      setResult(finalData);
      console.log("Success:", finalData);

    } catch (error) {
      // Handle server errors or timeouts
      console.error("Task failed:", error);
      alert(`Error: ${error.message}`);
    } finally {
      setIsLoading(false);
      setStatusText("");
    }
  };

  return (
    <div>
      <button onClick={handleRunTask} disabled={isLoading}>
        {isLoading ? "Running..." : "Start Task"}
      </button>
  
      {/* Display real-time status to the user */}
      {isLoading && <p>Status: {statusText}</p>}
  
      {result && <div>Done! Check console for data.</div>}
    </div>
  );
}
```
