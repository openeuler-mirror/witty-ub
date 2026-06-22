#include "urma_failure_403.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure403> g_urma("urma_403");

bool UrmaFailure403::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_start_health_check_thread") != std::string::npos &&
           message.find("Failed to create health epoll") != std::string::npos;
}

std::string UrmaFailure403::GetName() const
{
    return "epoll文件描述符创建或注册失败导致校验start、health、thread失败";
}

std::string UrmaFailure403::GetRootCauseDesc() const
{
    return "bondp_start_health_check_thread需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure403::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure403::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure403::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_start_health_check_thread，Failed to create health epoll。";
}

std::string UrmaFailure403::GetId() const
{
    return "urma_403";
}
} // namespace diag
