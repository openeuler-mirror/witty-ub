#include "urma_failure_497.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure497> g_urma("urma_497");

bool UrmaFailure497::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_query_device' \"$URMA_LOG_PATH\" "
                                    "2>/dev/null | grep -F 'device list name:' | grep -F 'does not match dev_name:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure497::GetName() const
{
    return "查询设备过程中依赖步骤失败";
}

std::string UrmaFailure497::GetRootCauseDesc() const
{
    return "函数用于查询设备，执行过程中依赖的参数校验、状态转换、下层provider调用或系统资源处理未成功，导致本次URMA操"
           "作失败。";
}

RootCause UrmaFailure497::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure497::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure497::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_query_device，device list name:，does not match dev_name:。";
}

std::string UrmaFailure497::GetId() const
{
    return "urma_497";
}

} // namespace diag
