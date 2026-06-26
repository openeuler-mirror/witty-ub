#include "urma_failure_384.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure384> g_urma("urma_384");

bool UrmaFailure384::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_post_send_wr_and_store") != std::string::npos &&
           message.find("Failed to convert jfs wr") != std::string::npos;
}

std::string UrmaFailure384::GetName() const
{
    return "投递工作请求、AND、store执行失败导致投递工作请求、AND、store失败";
}

std::string UrmaFailure384::GetRootCauseDesc() const
{
    return "bondp_post_send_wr_and_"
           "store执行投递工作请求、AND、store时依赖的投递工作请求、AND、store步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure384::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure384::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure384::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_post_send_wr_and_store，Failed to convert jfs wr。";
}

std::string UrmaFailure384::GetId() const
{
    return "urma_384";
}
} // namespace diag
