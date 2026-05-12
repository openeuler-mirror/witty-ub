#include "urma_0256_post_send_check_jfs_wr_valid_failure_wr_faa_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc> g_urma("urma_0256");

bool Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"when set faa_wr, either src or dst is NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::GetName() const
{
    return "post_send_check_jfs_wr_valid 设置属性失败（wr->faa.src == NULL || wr->faa.dst == NULL）";
}

std::string Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：when set faa_wr, either src or dst is NULL.";
}

std::string Urma0256PostSendCheckJfsWrValidFailureWrFaaSrc::GetId() const
{
    return "urma_0256";
}
} // namespace diag
