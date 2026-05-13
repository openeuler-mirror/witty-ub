#include "urma_0281_set_fadd_wr_ptseg_pjetty_failure_send_wr_faa_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc> g_urma("urma_0281");

bool Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"when set faa_wr, one of src or dst is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::GetName() const
{
    return "set_fadd_wr_ptseg_pjetty 设置属性失败（send_wr->faa.src == NULL || send_wr->faa.dst == NULL）";
}

std::string Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：when set faa_wr, one of src or dst is NULL.";
}

std::string Urma0281SetFaddWrPtsegPjettyFailureSendWrFaaSrc::GetId() const
{
    return "urma_0281";
}
} // namespace diag
