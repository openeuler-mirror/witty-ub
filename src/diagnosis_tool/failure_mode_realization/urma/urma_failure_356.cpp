#include "urma_failure_356.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure356> g_urma("urma_356");

bool UrmaFailure356::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vjfce") != std::string::npos &&
           message.find("Fail to create epoll_fd for vjfce.") != std::string::npos;
}

std::string UrmaFailure356::GetName() const
{
    return "epoll文件描述符创建或注册失败导致创建虚拟JFCE失败";
}

std::string UrmaFailure356::GetRootCauseDesc() const
{
    return "bondp_create_vjfce需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure356::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure356::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure356::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vjfce，Fail to create epoll_fd for vjfce.。";
}

std::string UrmaFailure356::GetId() const
{
    return "urma_356";
}
} // namespace diag
