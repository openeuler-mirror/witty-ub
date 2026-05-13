#include "urma_0263_resend_wr_from_node_failure.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0263ResendWrFromNodeFailure> g_urma("urma_0263");

bool Urma0263ResendWrFromNodeFailure::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set ptseg_ptjetty"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0263ResendWrFromNodeFailure::GetName() const
{
    return "resend_wr_from_node 设置属性失败";
}

std::string Urma0263ResendWrFromNodeFailure::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "ret";
}

RootCause Urma0263ResendWrFromNodeFailure::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0263ResendWrFromNodeFailure::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0263ResendWrFromNodeFailure::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set ptseg_ptjetty";
}

std::string Urma0263ResendWrFromNodeFailure::GetId() const
{
    return "urma_0263";
}
} // namespace diag
