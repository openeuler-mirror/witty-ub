#include "urma_failure_564.h"
#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure564> g_urma("urma_564");

bool UrmaFailure564::IsValid()
{
    std::string grepOutput =
        urma_log_helper::RunCommand("test -n \"$URMA_LOG_PATH\" && grep -F 'handle_fake_cr_with_store' "
                                    "\"$URMA_LOG_PATH\" 2>/dev/null | grep -F 'Invalid cr error status:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure564::GetName() const
{
    return "执行URMA资源所需输入对象无效导致刷出虚拟 Jetty失败";
}

std::string UrmaFailure564::GetRootCauseDesc() const
{
    return "函数用于刷出虚拟 Jetty，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure564::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure564::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure564::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_fake_cr_with_store，Invalid cr error status:。";
}

std::string UrmaFailure564::GetId() const
{
    return "urma_564";
}

} // namespace diag
