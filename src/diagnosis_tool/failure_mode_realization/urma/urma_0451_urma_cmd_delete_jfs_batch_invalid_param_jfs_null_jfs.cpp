#include "urma_0451_urma_cmd_delete_jfs_batch_invalid_param_jfs_null_jfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs> g_urma("urma_0451");

bool Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter, index: %."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::GetName() const
{
    return "urma_cmd_delete_jfs_batch 参数非法（jfs == NULL || jfs->urma_ctx == NULL）";
}

std::string Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || jfs->urma_ctx == NULL`；该路径返回 URMA_EINVAL";
}

RootCause Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter, index: %.";
}

std::string Urma0451UrmaCmdDeleteJfsBatchInvalidParamJfsNullJfs::GetId() const
{
    return "urma_0451";
}
} // namespace diag
