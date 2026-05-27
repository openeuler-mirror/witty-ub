#include "urma_failure_108.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure108> g_urma("urma_108");

bool UrmaFailure108::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_register_health_check_task' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to register health task: no valid route'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure108::GetName() const
{
    return "未找到可用于注册健康检查的有效对象或路由";
}

std::string UrmaFailure108::GetRootCauseDesc() const
{
    return "函数在注册健康检查过程中需要查找已建立的资源、端口或路由映射，但当前表项缺失或状态不可用，导致后续操作无法"
           "定位目标。";
}

RootCause UrmaFailure108::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure108::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure108::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_register_health_check_task，Failed to register health task: no valid route";
}

std::string UrmaFailure108::GetId() const
{
    return "urma_108";
}

} // namespace diag
