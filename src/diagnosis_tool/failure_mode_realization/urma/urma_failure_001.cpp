#include "urma_failure_001.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure001> g_urma("urma_001");

bool UrmaFailure001::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'init_active_indices' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Invalid port_count:'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure001::GetName() const
{
    return "初始化URMA资源所需输入对象无效导致初始化端口失败";
}

std::string UrmaFailure001::GetRootCauseDesc() const
{
    return "函数用于初始化端口，调用方传入的初始化URMA资源所需输入对象不满足接口前置条件，无法继续完成本次URMA操作。";
}

RootCause UrmaFailure001::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure001::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure001::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：init_active_indices，Invalid port_count:";
}

std::string UrmaFailure001::GetId() const
{
    return "urma_001";
}

} // namespace diag
