#include "urma_failure_858.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure858> g_urma("urma_858");

bool UrmaFailure858::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'urma_getenv_log_level' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid parameter: log level str.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure858::GetName() const
{
    return "执行URMA资源所需输入对象无效导致获取URMA资源失败";
}

std::string UrmaFailure858::GetRootCauseDesc() const
{
    return "函数用于获取URMA资源，调用方传入的执行URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure858::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure858::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure858::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：urma_getenv_log_level，Invalid parameter: log level str.";
}

std::string UrmaFailure858::GetId() const
{
    return "urma_858";
}

} // namespace diag
