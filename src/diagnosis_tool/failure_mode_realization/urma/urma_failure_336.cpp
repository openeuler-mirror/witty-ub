#include "urma_failure_336.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure336> g_urma("urma_336");

bool UrmaFailure336::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_health_check_ctx' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create health task table'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure336::GetName() const
{
    return "健康检查创建时下层资源准备失败";
}

std::string UrmaFailure336::GetRootCauseDesc() const
{
    return "函数负责创建健康检查，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure336::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure336::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure336::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_health_check_ctx，Failed to create health task table";
}

std::string UrmaFailure336::GetId() const
{
    return "urma_336";
}

} // namespace diag
