#include "urma_failure_734.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure734> g_urma("urma_734");

bool UrmaFailure734::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'wait_async_event_ack' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'There is an event and it must be acked, acked:' | grep -F ', reported:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure734::GetName() const
{
    return "等待锁过程中依赖步骤失败";
}

std::string UrmaFailure734::GetRootCauseDesc() const
{
    return "函数用于等待锁，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操作"
           "失败。";
}

RootCause UrmaFailure734::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure734::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure734::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：wait_async_event_ack，There is an event and it must be acked, acked:，, "
           "reported:";
}

std::string UrmaFailure734::GetId() const
{
    return "urma_734";
}

} // namespace diag
