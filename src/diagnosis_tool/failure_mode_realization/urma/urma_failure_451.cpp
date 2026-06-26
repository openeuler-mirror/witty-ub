#include "urma_failure_451.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure451> g_urma("urma_451");

bool UrmaFailure451::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfc") != std::string::npos &&
           message.find("[DRV_ERR]Failed to delete jfc, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", id:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure451::GetName() const
{
    return "下层资源删除失败导致删除JFC失败";
}

std::string UrmaFailure451::GetRootCauseDesc() const
{
    return "urma_delete_jfc清理JFC时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure451::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure451::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure451::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfc，[DRV_ERR]Failed to delete jfc, dev_name:，, "
           "eid_idx:，, id:，, r"
           "et:。";
}

std::string UrmaFailure451::GetId() const
{
    return "urma_451";
}
} // namespace diag
