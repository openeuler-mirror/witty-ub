#include "urma_failure_413.h"

#include "../../failure_mode_factory.h"

namespace diag {
static AutoRegister<UrmaFailure413> g_urma("urma_413");

bool UrmaFailure413::IsValid(const std::vector<std::string> &fields)
{
    const std::string &message = fields[7];
    return message.find("urma_cmd_delete_jfc") != std::string::npos &&
           message.find("There is jfc event and it must be acked, jfc_comp:") != std::string::npos &&
           message.find(", comp:") != std::string::npos && message.find(", jfc_async:") != std::string::npos &&
           message.find(", async:") != std::string::npos;
}

std::string UrmaFailure413::GetName() const
{
    return "JFC状态不满足要求导致删除JFC失败";
}

std::string UrmaFailure413::GetRootCauseDesc() const
{
    return "urma_cmd_delete_jfc执行删除JFC时检测到依赖对象、资源状态或返回值异常，因此中止当前URMA操作。";
}

RootCause UrmaFailure413::AnalyzeRootCause()
{
    return RootCause(false, GetRootCauseDesc());
}

std::string UrmaFailure413::GetFixSuggDesc() const
{
    return "无";
}

std::string UrmaFailure413::GetValidationMethodDesc() const
{
    return "通过 URMA_LOG_PATH 日志匹配关键字：urma_cmd_delete_jfc，There is jfc event and it must be acked, "
           "jfc_comp:，, comp"
           ":，, jfc_async:，, async:。";
}

std::string UrmaFailure413::GetId() const
{
    return "urma_413";
}
} // namespace diag
