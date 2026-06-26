#include "urma_failure_394.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure394> g_urma("urma_394");

bool UrmaFailure394::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("handle_send_cr_with_store") != std::string::npos &&
           message.find("Failed to resend jfs wr, wr_id:") != std::string::npos;
}

std::string UrmaFailure394::GetName() const
{
    return "发送handle、CR、WITH执行失败导致发送handle、CR、WITH失败";
}

std::string UrmaFailure394::GetRootCauseDesc() const
{
    return "handle_send_cr_with_"
           "store执行发送handle、CR、WITH时依赖的发送handle、CR、WITH步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure394::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure394::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure394::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_send_cr_with_store，Failed to resend jfs wr, wr_id:。";
}

std::string UrmaFailure394::GetId() const
{
    return "urma_394";
}
} // namespace diag
