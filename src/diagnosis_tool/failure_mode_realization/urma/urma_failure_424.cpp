#include "urma_failure_424.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure424> g_urma("urma_424");

bool UrmaFailure424::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_free_jfc") != std::string::npos &&
           message.find("There is jfc event and it must be acked, jfc_comp:") != std::string::npos &&
           message.find(", comp:") != std::string::npos && message.find(", jfc_async:") != std::string::npos &&
           message.find(", async:") != std::string::npos;
}

std::string UrmaFailure424::GetName() const
{
    return "JFC状态不满足要求导致释放JFC失败";
}

std::string UrmaFailure424::GetRootCauseDesc() const
{
    return "urma_cmd_free_jfc执行释放JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure424::AnalyzeRootCause()
{
    return RootCause(true, GetRootCauseDesc());
}

std::string UrmaFailure424::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure424::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_free_jfc，There is jfc event and it must be acked, "
           "jfc_comp:，, comp:，"
           ", jfc_async:，, async:。";
}

std::string UrmaFailure424::GetId() const
{
    return "urma_424";
}
} // namespace diag
