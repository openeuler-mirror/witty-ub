#include "urma_failure_372.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure372> g_urma("urma_372");

bool UrmaFailure372::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_get_async_event") != std::string::npos &&
           message.find("epoll_wait no event or err.") != std::string::npos;
}

std::string UrmaFailure372::GetName() const
{
    return "epoll文件描述符创建或注册失败导致获取event失败";
}

std::string UrmaFailure372::GetRootCauseDesc() const
{
    return "bondp_get_async_event需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure372::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure372::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure372::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_get_async_event，epoll_wait no event or err.。";
}

std::string UrmaFailure372::GetId() const
{
    return "urma_372";
}
} // namespace diag
