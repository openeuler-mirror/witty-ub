#include "urma_failure_002.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure002> g_urma("urma_002");

bool UrmaFailure002::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'init_active_indices' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid active port id, value: 0x' | grep -F 'x.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure002::GetName() const
{
    return "初始化URMA资源所需输入对象无效导致激活端口失败";
}

std::string UrmaFailure002::GetRootCauseDesc() const
{
    return "函数用于激活端口，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure002::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure002::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure002::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：init_active_indices，Invalid active port id, value: 0x，x.";
}

std::string UrmaFailure002::GetId() const
{
    return "urma_002";
}

} // namespace diag
