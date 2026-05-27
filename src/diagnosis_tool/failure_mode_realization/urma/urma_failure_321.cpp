#include "urma_failure_321.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure321> g_urma("urma_321");

bool UrmaFailure321::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_vjfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Fail to create epoll_fd for vjfce.'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure321::GetName() const
{
    return "epoll创建时下层资源准备失败";
}

std::string UrmaFailure321::GetRootCauseDesc() const
{
    return "函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure321::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure321::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure321::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_vjfce，Fail to create epoll_fd for vjfce.";
}

std::string UrmaFailure321::GetId() const
{
    return "urma_321";
}

} // namespace diag
