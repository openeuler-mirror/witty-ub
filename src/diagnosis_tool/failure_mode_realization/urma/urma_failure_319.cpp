#include "urma_failure_319.h"

#include "../../failure_mode_factory.h"
#include "urma_log_helper.h"

namespace diag {

static AutoRegister<UrmaFailure319> g_urma("urma_319");

bool UrmaFailure319::IsValid()
{
    std::string grepOutput = urma_log_helper::RunCommand(
        "test -n \"$URMA_LOG_PATH\" && grep -F 'bondp_create_pjfce' \"$URMA_LOG_PATH\" 2>/dev/null | "
        "grep -F 'Failed to create pjfce'");
    FailureLogInfo &logInfo = GetMutableFailureLogInfoCache();
    urma_log_helper::ParseFailureLogLine(grepOutput, logInfo);
    return !grepOutput.empty();
}

std::string UrmaFailure319::GetName() const
{
    return "epoll创建时下层资源准备失败";
}

std::string UrmaFailure319::GetRootCauseDesc() const
{
    return "函数负责创建epoll，依赖的provider接口、驱动命令、子资源或路由信息未成功返回，导致资源无法建立。";
}

RootCause UrmaFailure319::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure319::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure319::GetValidationMethodDesc() const
{
    return "通过 URMA 日志关键字校验：bondp_create_pjfce，Failed to create pjfce";
}

std::string UrmaFailure319::GetId() const
{
    return "urma_319";
}

} // namespace diag
