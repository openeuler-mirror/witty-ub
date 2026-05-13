#include "urma_0283_set_fadd_wr_ptseg_pjetty_failure_vtseg_null.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0283SetFaddWrPtsegPjettyFailureVtsegNull> g_urma("urma_0283");

bool Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Failed to set ptseg, vtseg is NULL"};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 设置属性失败（vtseg == NULL）";
}

std::string Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Failed to set ptseg, vtseg is NULL";
}

std::string Urma0283SetFaddWrPtsegPjettyFailureVtsegNull::GetId() const
{
    return "urma_0283";
}
} // namespace diag
