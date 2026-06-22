#include "urma_failure_373.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure373> g_urma("urma_373");

bool UrmaFailure373::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_get_async_event") != std::string::npos &&
           message.find("bondp get error epoll_event: 0x") != std::string::npos;
}

std::string UrmaFailure373::GetName() const
{
    return "epoll文件描述符创建或注册失败导致获取event失败";
}

std::string UrmaFailure373::GetRootCauseDesc() const
{
    return "bondp_get_async_event需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure373::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure373::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure373::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，bondp get error epoll_event: 0x。";
}

std::string UrmaFailure373::GetId() const
{
    return "urma_373";
}
} // namespace diag
