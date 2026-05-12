#include "urma_0255_post_send_check_jfs_wr_valid_failure_wr_cas_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0255PostSendCheckJfsWrValidFailureWrCasSrc> g_urma("urma_0255");

bool Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"when set cas_wr, either src or dst is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::GetName() const
{
    return "post_send_check_jfs_wr_valid 设置属性失败（wr->cas.src == NULL || wr->cas.dst == NULL）";
}

std::string Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：when set cas_wr, either src or dst is NULL.";
}

std::string Urma0255PostSendCheckJfsWrValidFailureWrCasSrc::GetId() const
{
    return "urma_0255";
}
} // namespace diag
