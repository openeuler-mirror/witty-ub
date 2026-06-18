#include "urma_failure_517.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure517> g_urma("urma_517");

bool UrmaFailure517::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("bondp_delete_pcontext") != std::string::npos &&
           message.find("Failed to delete pctx, idx:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure517::GetName() const
{
    return "下层资源删除失败导致删除pcontext失败";
}

std::string UrmaFailure517::GetRootCauseDesc() const
{
    return "bondp_delete_pcontext清理pcontext时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure517::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure517::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure517::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：bondp_delete_pcontext，Failed to delete pctx, idx:，, ret:。";
}

std::string UrmaFailure517::GetId() const
{
    return "urma_517";
}
} // namespace diag
