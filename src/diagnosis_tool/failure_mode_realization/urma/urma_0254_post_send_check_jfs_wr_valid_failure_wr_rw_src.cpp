#include "urma_0254_post_send_check_jfs_wr_valid_failure_wr_rw_src.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0254PostSendCheckJfsWrValidFailureWrRwSrc> g_urma("urma_0254");

bool Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {
        "when set write_wr, either of src/dst num_sge/sge has been set zero or NULL."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::GetName() const
{
    return "post_send_check_jfs_wr_valid 设置属性失败（wr->rw.src.num_sge == 0 || wr->rw.dst.num_sge == 0 || "
           "wr->rw.src.sge == NULL || wr->rw.dst.sge == NU）";
}

std::string Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::GetRootCauseDesc() const
{
    return "资源操作失败，可能由于对象状态不匹配、参数非法、设备能力不支持或下游 provider/driver 返回错误；该路径返回 "
           "URMA_EINVAL";
}

RootCause Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：when set write_wr, either of src/dst num_sge/sge has been set "
           "zero or NULL.";
}

std::string Urma0254PostSendCheckJfsWrValidFailureWrRwSrc::GetId() const
{
    return "urma_0254";
}
} // namespace diag
