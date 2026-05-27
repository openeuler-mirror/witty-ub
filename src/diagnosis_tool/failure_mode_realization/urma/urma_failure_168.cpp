#include "urma_failure_168.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure168> g_urma("urma_168");

bool UrmaFailure168::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_cmd_import_jetty_async' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure168::GetName() const
{
    return "URMA context、sysfs设备信息、目标Jetty对象无效导致导入Jetty失败";
}

std::string UrmaFailure168::GetRootCauseDesc() const
{
    return "函数用于导入Jetty，调用方传入的URMA "
           "context、sysfs设备信息、目标Jetty对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure168::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure168::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure168::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_import_jetty_async，Invalid parameter。";
}

std::string UrmaFailure168::GetId() const
{
    return "urma_168";
}

} // namespace diag
