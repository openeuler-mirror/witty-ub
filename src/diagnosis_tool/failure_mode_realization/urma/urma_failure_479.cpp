#include "urma_failure_479.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure479> g_urma("urma_479");

bool UrmaFailure479::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_delete_jfce") != std::string::npos &&
           message.find("Jfce is still used by at least one jfc, refcnt:") != std::string::npos;
}

std::string UrmaFailure479::GetName() const
{
    return "JFCE状态不满足要求导致删除JFCE失败";
}

std::string UrmaFailure479::GetRootCauseDesc() const
{
    return "urma_delete_jfce执行删除JFCE时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure479::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure479::GetFixSuggDesc() const
{
    return "当前不会触发";
}

std::string UrmaFailure479::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_delete_jfce，Jfce is still used by at least one jfc, refcnt:。";
}

std::string UrmaFailure479::GetId() const
{
    return "urma_479";
}
} // namespace diag
