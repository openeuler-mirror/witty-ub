#include "urma_failure_477.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure477> g_urma("urma_477");

bool UrmaFailure477::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_create_jfce") != std::string::npos &&
           message.find("[DRV_ERR]Failed to create jfce, dev_name:") != std::string::npos &&
           message.find(", eid_idx:") != std::string::npos;
}

std::string UrmaFailure477::GetName() const
{
    return "下层资源创建失败导致创建JFCE失败";
}

std::string UrmaFailure477::GetRootCauseDesc() const
{
    return "urma_create_jfce在创建JFCE过程中依赖下层对象或provider创建结果，下层返回失败后当前资源无法建立。";
}

RootCause UrmaFailure477::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure477::GetFixSuggDesc() const
{
    return "当前预期不会出现，如果fd超规格可能导致失败，此时需要修改系统fd规格数，或者减小应用创建jfce的数量";
}

std::string UrmaFailure477::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_create_jfce，[DRV_ERR]Failed to create jfce, dev_name:，, "
           "eid_idx:。";
}

std::string UrmaFailure477::GetId() const
{
    return "urma_477";
}
} // namespace diag
