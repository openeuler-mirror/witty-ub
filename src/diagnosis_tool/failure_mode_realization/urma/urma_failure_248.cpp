#include "urma_failure_248.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure248> g_urma("urma_248");

bool UrmaFailure248::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfr") != std::string::npos &&
           message.find("[DRV_ERR]Failed to delete jfr, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", id:") != std::string::npos &&
           message.find(", status:") != std::string::npos;
}

std::string UrmaFailure248::GetName() const
{
    return "下层资源删除失败导致删除JFR失败";
}

std::string UrmaFailure248::GetRootCauseDesc() const
{
    return "urma_delete_jfr清理JFR时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure248::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure248::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure248::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfr，[DRV_ERR]Failed to delete jfr, dev_name:，, "
           "eid_idx:，, id:，, s"
           "tatus:。";
}

std::string UrmaFailure248::GetId() const
{
    return "urma_248";
}
} // namespace diag
