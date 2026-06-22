#include "urma_failure_255.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure255> g_urma("urma_255");

bool UrmaFailure255::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jetty") != std::string::npos &&
           message.find("[DRV_ERR]Failed to delete jetty, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos && message.find(", id:") != std::string::npos &&
           message.find(", ret:") != std::string::npos;
}

std::string UrmaFailure255::GetName() const
{
    return "下层资源删除失败导致删除Jetty失败";
}

std::string UrmaFailure255::GetRootCauseDesc() const
{
    return "urma_delete_jetty清理Jetty时需要同步删除关联的下层对象，任一删除步骤返回失败都会使资源清理不完整。";
}

RootCause UrmaFailure255::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure255::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure255::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jetty，[DRV_ERR]Failed to delete jetty, dev_name:，, "
           "eid_idx:，, id:"
           "，, ret:。";
}

std::string UrmaFailure255::GetId() const
{
    return "urma_255";
}
} // namespace diag
