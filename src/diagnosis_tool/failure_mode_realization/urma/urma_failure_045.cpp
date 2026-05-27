#include "urma_failure_045.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure045> g_urma("urma_045");

bool UrmaFailure045::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'urma_unregister_provider_ops' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid parameter.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure045::GetName() const
{
    return "provider操作表无效导致注销URMA资源失败";
}

std::string UrmaFailure045::GetRootCauseDesc() const
{
    return "函数用于注销URMA资源，调用方传入的provider操作表不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure045::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure045::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure045::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_unregister_provider_ops，Invalid parameter.。";
}

std::string UrmaFailure045::GetId() const
{
    return "urma_045";
}

} // namespace diag
