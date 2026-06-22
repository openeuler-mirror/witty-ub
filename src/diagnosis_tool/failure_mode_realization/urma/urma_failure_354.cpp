#include "urma_failure_354.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure354> g_urma("urma_354");

bool UrmaFailure354::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_pjfce") != std::string::npos &&
           message.find("Fail to add fd:") != std::string::npos && message.find("to epoll fd:") != std::string::npos;
}

std::string UrmaFailure354::GetName() const
{
    return "epoll文件描述符创建或注册失败导致创建物理JFCE失败";
}

std::string UrmaFailure354::GetRootCauseDesc() const
{
    return "bondp_create_pjfce需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure354::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure354::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure354::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_pjfce，Fail to add fd:，to epoll fd:。";
}

std::string UrmaFailure354::GetId() const
{
    return "urma_354";
}
} // namespace diag
