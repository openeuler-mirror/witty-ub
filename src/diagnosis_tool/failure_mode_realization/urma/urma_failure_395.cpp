#include "urma_failure_395.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure395> g_urma("urma_395");

bool UrmaFailure395::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("handle_recv_cr_with_store") != std::string::npos &&
           message.find("Failed to find local jetty, idx:") != std::string::npos &&
           message.find(", id:") != std::string::npos;
}

std::string UrmaFailure395::GetName() const
{
    return "接收handle、CR、WITH执行失败导致接收handle、CR、WITH失败";
}

std::string UrmaFailure395::GetRootCauseDesc() const
{
    return "handle_recv_cr_with_"
           "store执行接收handle、CR、WITH时依赖的接收handle、CR、WITH步骤返回错误，当前URMA操作无法继续完成。";
}

RootCause UrmaFailure395::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure395::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure395::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：handle_recv_cr_with_store，Failed to find local jetty, idx:，, id:。";
}

std::string UrmaFailure395::GetId() const
{
    return "urma_395";
}
} // namespace diag
