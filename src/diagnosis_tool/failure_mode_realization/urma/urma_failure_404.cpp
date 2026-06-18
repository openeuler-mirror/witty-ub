#include "urma_failure_404.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure404> g_urma("urma_404");

bool UrmaFailure404::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_create_health_check_ctx") != std::string::npos &&
           message.find("Failed to add ctx async fd to health epoll, errno:") != std::string::npos;
}

std::string UrmaFailure404::GetName() const
{
    return "epoll文件描述符创建或注册失败导致创建health、context失败";
}

std::string UrmaFailure404::GetRootCauseDesc() const
{
    return "bondp_create_health_check_ctx需要将URMA事件fd纳入epoll管理，系统调用失败会导致完成事件无法被统一监听。";
}

RootCause UrmaFailure404::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure404::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure404::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_create_health_check_ctx，Failed to add ctx async fd to health "
           "epoll, err"
           "no:。";
}

std::string UrmaFailure404::GetId() const
{
    return "urma_404";
}
} // namespace diag
