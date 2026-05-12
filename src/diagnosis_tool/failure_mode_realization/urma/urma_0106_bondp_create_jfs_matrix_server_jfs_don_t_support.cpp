#include "urma_0106_bondp_create_jfs_matrix_server_jfs_don_t_support.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0106BondpCreateJfsMatrixServerJfsDonTSupport> g_urma("urma_0106");

bool Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"In matrix server, JFS don't support single-path mode."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::GetName() const
{
    return "bondp_create_jfs In matrix server, JFS don't support";
}

std::string Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::GetRootCauseDesc() const
{
    return "错误分支触发条件为 `cfg->flag.bs.multi_path == false`；该路径返回 NULL";
}

RootCause Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：In matrix server, JFS don't support single-path mode.";
}

std::string Urma0106BondpCreateJfsMatrixServerJfsDonTSupport::GetId() const
{
    return "urma_0106";
}
} // namespace diag
