#include "urma_failure_382.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure382> g_urma("urma_382");

bool UrmaFailure382::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_send_wr_and_store") != std::string::npos &&
           message.find("Failed to allocate jfs wr entry") != std::string::npos;
}

std::string UrmaFailure382::GetName() const
{
    return "工作请求、AND、store临时结构分配失败导致投递工作请求、AND、store失败";
}

std::string UrmaFailure382::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_and_"
           "store执行投递工作请求、AND、store前需要准备工作请求、AND、store临时结构，内存或资源分配失败会阻断后续URMA操"
           "作。";
}

RootCause UrmaFailure382::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure382::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure382::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，Failed to allocate jfs wr entry。";
}

std::string UrmaFailure382::GetId() const
{
    return "urma_382";
}
} // namespace diag
