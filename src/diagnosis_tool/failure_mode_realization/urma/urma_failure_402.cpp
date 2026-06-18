#include "urma_failure_402.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure402> g_urma("urma_402");

bool UrmaFailure402::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_health_check_thread") != std::string::npos &&
           message.find("Health check epoll_wait failed, errno:") != std::string::npos;
}

std::string UrmaFailure402::GetName() const
{
    return "epoll文件描述符创建或注册失败导致校验health、thread失败";
}

std::string UrmaFailure402::GetRootCauseDesc() const
{
    return "bondp_health_check_thread需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure402::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure402::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure402::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_health_check_thread，Health check epoll_wait failed, errno:。";
}

std::string UrmaFailure402::GetId() const
{
    return "urma_402";
}
} // namespace diag
