#include "urma_0607_urma_advise_jfr_invalid_param_jfs_null_tjfr_null_jfs.h"
#include <vector>
#include "../../failure_mode_factory.h"
#include "urma_log_matcher.h"

namespace diag {

static AutoRegister<Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs> g_urma("urma_0607");

bool Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::IsValid(std::string &logContent)
{
    logContent.clear();
    const std::vector<std::string> patterns = {"Invalid parameter."};
    return MatchUrmaLogLine(patterns, logContent);
}

std::string Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::GetName() const
{
    return "urma_advise_jfr 参数非法（jfs == NULL || tjfr == NULL || (jfs->jfs_cfg.trans_mode != URMA_TM_RM || "
           "tjfr->trans_mode != URMA_TM）";
}

std::string Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::GetRootCauseDesc() const
{
    return "函数参数校验失败，触发条件为 `jfs == NULL || tjfr == NULL || (jfs->jfs_cfg.trans_mode != URMA_TM_RM || "
           "tjfr->trans_mode != URMA_TM`；该路径返回 URMA_EINVAL";
}

RootCause Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::GetFixSuggDesc() const
{
    return "无";
}

std::string Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::GetValidationMethodDesc() const
{
    return "在 URMA_LOG_PATH 指定日志中匹配关键日志：Invalid parameter.";
}

std::string Urma0607UrmaAdviseJfrInvalidParamJfsNullTjfrNullJfs::GetId() const
{
    return "urma_0607";
}
} // namespace diag
