#include "urma_failure_383.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure383> g_urma("urma_383");

bool UrmaFailure383::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_send_wr_and_store") != std::string::npos &&
           message.find("Failed to copy jfs wr") != std::string::npos;
}

std::string UrmaFailure383::GetName() const
{
    return "投递工作请求、AND、store执行失败导致投递工作请求、AND、store失败";
}

std::string UrmaFailure383::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_and_"
           "store执行投递工作请求、AND、store时依赖的投递工作请求、AND、store步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure383::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure383::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure383::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，Failed to copy jfs wr。";
}

std::string UrmaFailure383::GetId() const
{
    return "urma_383";
}
} // namespace diag
