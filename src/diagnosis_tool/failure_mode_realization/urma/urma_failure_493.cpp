#include "urma_failure_493.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure493> g_urma("urma_493");

bool UrmaFailure493::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'device list name:' | grep -F 'does not match dev_name:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure493::GetName() const
{
    return "查询设备过程中依赖步骤失败";
}

std::string UrmaFailure493::GetRootCauseDesc() const
{
    return "函数用于查询设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure493::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure493::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure493::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_query_device，device list name:，does not match dev_name:";
}

std::string UrmaFailure493::GetId() const
{
    return "urma_493";
}

} // namespace diag
