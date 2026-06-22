#include "urma_failure_405.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure405> g_urma("urma_405");

bool UrmaFailure405::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_vcontext") != std::string::npos &&
           message.find("Failed to create epoll") != std::string::npos;
}

std::string UrmaFailure405::GetName() const
{
    return "epoll文件描述符创建或注册失败导致创建vcontext失败";
}

std::string UrmaFailure405::GetRootCauseDesc() const
{
    return "bondp_create_vcontext需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure405::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure405::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure405::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_vcontext，Failed to create epoll。";
}

std::string UrmaFailure405::GetId() const
{
    return "urma_405";
}
} // namespace diag
