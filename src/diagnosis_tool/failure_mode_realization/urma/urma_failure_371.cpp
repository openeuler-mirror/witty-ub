#include "urma_failure_371.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure371> g_urma("urma_371");

bool UrmaFailure371::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_wait_jfc") != std::string::npos &&
           message.find("Epoll wait err, ret:") != std::string::npos;
}

std::string UrmaFailure371::GetName() const
{
    return "epoll文件描述符创建或注册失败导致waitWAIT、JFC失败";
}

std::string UrmaFailure371::GetRootCauseDesc() const
{
    return "bondp_wait_jfc需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure371::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure371::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure371::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_wait_jfc，Epoll wait err, ret:。";
}

std::string UrmaFailure371::GetId() const
{
    return "urma_371";
}
} // namespace diag
