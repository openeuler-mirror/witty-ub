#include "urma_failure_243.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure243> g_urma("urma_243");

bool UrmaFailure243::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfs") != std::string::npos &&
           message.find("[DRV_ERR]Failed to delete jfs, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", id:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure243::GetName() const
{
    return "下层资源删除失败导致删除JFS失败";
}

std::string UrmaFailure243::GetRootCauseDesc() const
{
    return "urma_delete_jfs清理JFS时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure243::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure243::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure243::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfs，[DRV_ERR]Failed to delete jfs, dev_name:，, "
           "eid_idx:，, id:，, r"
           "et:。";
}

std::string UrmaFailure243::GetId() const
{
    return "urma_243";
}
} // namespace diag
