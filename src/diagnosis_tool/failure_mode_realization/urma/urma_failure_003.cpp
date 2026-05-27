#include "urma_failure_003.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure003> g_urma("urma_003");

bool UrmaFailure003::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'init_target_active_indices' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to find connected port'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure003::GetName() const
{
    return "未找到可用于初始化端口的有效对象或路由";
}

std::string UrmaFailure003::GetRootCauseDesc() const
{
    return "函数在初始化端口过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法定"
           "位目标。";
}

RootCause UrmaFailure003::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure003::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure003::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：init_target_active_indices，Failed to find connected port";
}

std::string UrmaFailure003::GetId() const
{
    return "urma_003";
}

} // namespace diag
