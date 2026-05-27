#include "urma_failure_343.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure343> g_urma("urma_343");

bool UrmaFailure343::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vcontext' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create epoll'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure343::GetName() const
{
    return "epoll创建时下层资源准备失败";
}

std::string UrmaFailure343::GetRootCauseDesc() const
{
    return "函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure343::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure343::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure343::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vcontext，Failed to create epoll";
}

std::string UrmaFailure343::GetId() const
{
    return "urma_343";
}

} // namespace diag
